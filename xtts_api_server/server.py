import multiprocessing
from TTS.api import TTS
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse,StreamingResponse

from pydantic import BaseModel
import uvicorn

import os
import time
from pathlib import Path
import shutil
from loguru import logger
from argparse import ArgumentParser
from pathlib import Path
from uuid import uuid4
import asyncio

from xtts_api_server.tts_funcs import TTSWrapper,supported_languages,InvalidSettingsError
from xtts_api_server.RealtimeTTS import TextToAudioStream, CoquiEngine
from xtts_api_server.modeldownloader import check_stream2sentence_version,install_deepspeed_based_on_python_version

# Set the multiprocessing start method
multiprocessing.set_start_method("spawn", force=True)

# Default Folders , you can change them via API
DEVICE = os.getenv('DEVICE',"cuda")
OUTPUT_FOLDER = os.getenv('OUTPUT', 'output')
SPEAKER_FOLDER = os.getenv('SPEAKER', 'speakers')
MODEL_FOLDER = os.getenv('MODEL', 'models')
BASE_HOST = os.getenv('BASE_URL', '127.0.0.1:8020')
BASE_URL = os.getenv('BASE_URL', '127.0.0.1:8020')
MODEL_SOURCE = os.getenv("MODEL_SOURCE", "local")
MODEL_VERSION = os.getenv("MODEL_VERSION","v2.0.2")
LOWVRAM_MODE = os.getenv("LOWVRAM_MODE") == 'true'
DEEPSPEED = os.getenv("DEEPSPEED") == 'true'
USE_CACHE = os.getenv("USE_CACHE") == 'true'

# STREAMING VARS
STREAM_MODE = os.getenv("STREAM_MODE") == 'true'
STREAM_MODE_IMPROVE = os.getenv("STREAM_MODE_IMPROVE") == 'true'
STREAM_PLAY_SYNC = os.getenv("STREAM_PLAY_SYNC") == 'true'

if(DEEPSPEED):
  install_deepspeed_based_on_python_version()

# Add a lock for thread safety
engine_lock = asyncio.Lock()

# Create an instance of the TTSWrapper class and server
app = FastAPI()
XTTS = TTSWrapper(OUTPUT_FOLDER,SPEAKER_FOLDER,MODEL_FOLDER,LOWVRAM_MODE,MODEL_SOURCE,MODEL_VERSION,DEVICE,DEEPSPEED,USE_CACHE)

# Check for old format model version
XTTS.model_version = XTTS.check_model_version_old_format(MODEL_VERSION)
MODEL_VERSION = XTTS.model_version

# Create version string
version_string = ""
if MODEL_SOURCE == "api" or MODEL_VERSION == "main":
    version_string = "lastest"
else:
    version_string = MODEL_VERSION

# Load model
if STREAM_MODE or STREAM_MODE_IMPROVE:
    # Load model for Streaming
    check_stream2sentence_version()

    logger.warning("'Streaming Mode' has certain limitations, you can read about them here https://github.com/daswer123/xtts-api-server#about-streaming-mode")

    if STREAM_MODE_IMPROVE:
        logger.info("You launched an improved version of streaming, this version features an improved tokenizer and more context when processing sentences, which can be good for complex languages like Chinese")
        
    model_path = XTTS.model_folder
    
    engine = CoquiEngine(specific_model=MODEL_VERSION,use_deepspeed=DEEPSPEED,local_models_path=str(model_path))
    stream = TextToAudioStream(engine)
else:
  logger.info(f"Model: '{version_string}' starts to load,wait until it loads")
  XTTS.load_model() 

if USE_CACHE:
    logger.info("You have enabled caching, this option enables caching of results, your results will be saved and if there is a repeat request, you will get a file instead of generation")

# Add CORS middleware 
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Help funcs
def play_stream(stream,language):
  if STREAM_MODE_IMPROVE:
    # Here we define common arguments in a dictionary for DRY principle
    play_args = {
        'minimum_sentence_length': 2,
        'minimum_first_fragment_length': 2,
        'tokenizer': "stanza",
        'language': language,
        'context_size': 2
    }
    if STREAM_PLAY_SYNC:
        # Play synchronously
        stream.play(**play_args)
    else:
        # Play asynchronously
        stream.play_async(**play_args)
  else:
    # If not improve mode just call the appropriate method based on sync_play flag.
    if STREAM_PLAY_SYNC:
      stream.play()
    else:
      stream.play_async()

class OutputFolderRequest(BaseModel):
    output_folder: str

class SpeakerFolderRequest(BaseModel):
    speaker_folder: str

class ModelNameRequest(BaseModel):
    model_name: str

class TTSSettingsRequest(BaseModel):
    stream_chunk_size: int
    temperature: float
    speed: float
    length_penalty: float
    repetition_penalty: float
    top_p: float
    top_k: int
    enable_text_splitting: bool

class SynthesisRequest(BaseModel):
    text: str
    speaker_wav: str 
    language: str

class SynthesisFileRequest(BaseModel):
    text: str
    speaker_wav: str 
    language: str
    file_name_or_path: str  

@app.get("/speakers_list")
def get_speakers():
    speakers = XTTS.get_speakers()
    return speakers

@app.get("/speakers")
def get_speakers():
    speakers = XTTS.get_speakers_special()
    return speakers

@app.get("/languages")
def get_languages():
    languages = XTTS.list_languages()
    return {"languages": languages}

@app.get("/get_folders")
def get_folders():
    speaker_folder = XTTS.speaker_folder
    output_folder = XTTS.output_folder
    model_folder = XTTS.model_folder
    return {"speaker_folder": speaker_folder, "output_folder": output_folder,"model_folder":model_folder}

@app.get("/get_models_list")
def get_models_list():
    return XTTS.get_models_list()

@app.get("/get_tts_settings")
def get_tts_settings():
    settings = {**XTTS.tts_settings,"stream_chunk_size":XTTS.stream_chunk_size}
    return settings

@app.get("/sample/{file_name:path}")
def get_sample(file_name: str):
    # A fix for path traversal vulenerability. 
    # An attacker may summon this endpoint with ../../etc/passwd and recover the password file of your PC (in linux) or access any other file on the PC
    if ".." in file_name:
        raise HTTPException(status_code=404, detail=".. in the file name! Are you kidding me?") 
    file_path = os.path.join(XTTS.speaker_folder, file_name)
    if os.path.isfile(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    else:
        logger.error("File not found")
        raise HTTPException(status_code=404, detail="File not found")

@app.post("/set_output")
def set_output(output_req: OutputFolderRequest):
    try:
        XTTS.set_out_folder(output_req.output_folder)
        return {"message": f"Output folder set to {output_req.output_folder}"}
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/set_speaker_folder")
def set_speaker_folder(speaker_req: SpeakerFolderRequest):
    try:
        XTTS.set_speaker_folder(speaker_req.speaker_folder)
        return {"message": f"Speaker folder set to {speaker_req.speaker_folder}"}
    except ValueError as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/switch_model")
def switch_model(modelReq: ModelNameRequest):
    try:
        XTTS.switch_model(modelReq.model_name)
        return {"message": f"Model switched to {modelReq.model_name}"}
    except InvalidSettingsError as e:  
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/set_tts_settings")
def set_tts_settings_endpoint(tts_settings_req: TTSSettingsRequest):
    try:
        XTTS.set_tts_settings(**tts_settings_req.dict())
        return {"message": "Settings successfully applied"}
    except InvalidSettingsError as e: 
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))

async def realtime_streaming_generator(request: Request, text: str, language: str, speaker_wav: str):
    import queue
    audio_queue = queue.Queue()
    generation_complete = asyncio.Event()

    def on_audio_chunk(chunk):
        audio_queue.put(chunk)

    def on_generation_complete():
        generation_complete.set()

    try:
        async with engine_lock:
            speaker_wav_path = XTTS.get_speaker_wav(speaker_wav)
            engine.set_voice(speaker_wav_path)
            engine.language = language.lower()

            # Create a new stream for each request to ensure thread safety
            stream = TextToAudioStream(engine)

        # Feed the text to the stream first
        stream.feed(text)
        
        # Then start streaming in a separate thread
        stream.play_async(
            fast_sentence_fragment=True,
            on_audio_chunk=on_audio_chunk,
            muted=True  # Important: mute local playback for network streaming
        )

        # Yield WAV header first
        yield XTTS.get_wav_header()
        
        while stream.is_playing() or not audio_queue.empty():
            try:
                chunk = audio_queue.get_nowait()
                yield chunk
            except queue.Empty:
                await asyncio.sleep(0.01)
                
        # Signal completion
        on_generation_complete()
               
    except Exception as e:
        logger.error(f"Error in real-time streaming: {e}")
        if await request.is_disconnected():
            logger.warning("Client disconnected during real-time streaming.")

@app.get('/tts_stream_realtime')
async def tts_stream_realtime(request: Request, text: str = Query(), speaker_wav: str = Query(), language: str = Query()):
    """
    Real-time streaming endpoint that sends audio chunks over the network as they're generated.
    This allows clients on different machines to receive and play audio in real-time.
    """
    if not (STREAM_MODE or STREAM_MODE_IMPROVE):
        raise HTTPException(status_code=400, detail="Real-time streaming requires STREAM_MODE or STREAM_MODE_IMPROVE to be enabled.")

    if language.lower() not in supported_languages:
        raise HTTPException(status_code=400, detail="Language code sent is either unsupported or misspelled.")

    return StreamingResponse(realtime_streaming_generator(request, text, language, speaker_wav), media_type="audio/wav")

@app.get('/tts_stream')
async def tts_stream(request: Request, text: str = Query(), speaker_wav: str = Query(), language: str = Query()):
    # Validate local model source.
    if XTTS.model_source != "local":
        raise HTTPException(status_code=400,
                            detail="HTTP Streaming is only supported for local models.")
    # Validate language code against supported languages.
    if language.lower() not in supported_languages:
        raise HTTPException(status_code=400,
                            detail="Language code sent is either unsupported or misspelled.")
            
    async def generator():
        chunks = XTTS.process_tts_to_file(
            text=text,
            speaker_name_or_path=speaker_wav,
            language=language.lower(),
            stream=True,
        )
        # Write file header to the output stream.
        yield XTTS.get_wav_header()
        async for chunk in chunks:
            # Check if the client is still connected.
            disconnected = await request.is_disconnected()
            if disconnected:
                break
            yield chunk

    return StreamingResponse(generator(), media_type='audio/x-wav')

@app.post("/tts_to_audio/")
async def tts_to_audio(request: SynthesisRequest, background_tasks: BackgroundTasks):
    # If streaming is enabled, handle the request in a streaming manner
    if STREAM_MODE or STREAM_MODE_IMPROVE:
        try:
            async with engine_lock:
                global stream
                # Validate language code against supported languages.
                if request.language.lower() not in supported_languages:
                    raise HTTPException(status_code=400,
                                        detail="Language code sent is either unsupported or misspelled.")

                speaker_wav = XTTS.get_speaker_wav(request.speaker_wav)
                language = request.language[0:2]

                if stream.is_playing() and not STREAM_PLAY_SYNC:
                    stream.stop()
                    stream = TextToAudioStream(engine)

                engine.set_voice(speaker_wav)
                engine.language = request.language.lower()

            # Feed the text to the stream and play
            stream.feed(request.text)
            play_stream(stream,language)

            return {"message": "Streaming started."}
        except Exception as e:
            logger.error(f"Error processing TTS request: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing TTS request: {e}")

    # If not streaming, handle the request in a non-streaming manner
    try:
        if XTTS.model_source == "local":
          logger.info(f"Processing TTS to audio with request: {request}")

        # Validate language code against supported languages.
        if request.language.lower() not in supported_languages:
            raise HTTPException(status_code=400,
                                detail="Language code sent is either unsupported or misspelled.")

        # Generate an audio file using process_tts_to_file.
        output_file_path = XTTS.process_tts_to_file(
            text=request.text,
            speaker_name_or_path=request.speaker_wav,
            language=request.language.lower(),
            file_name_or_path=f'{str(uuid4())}.wav'
        )

        if not XTTS.enable_cache_results:
            background_tasks.add_task(os.unlink, output_file_path)

        # Return the file in the response
        return FileResponse(
            path=output_file_path,
            media_type='audio/wav',
            filename="output.wav",
            )

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/tts_to_file")
async def tts_to_file(request: SynthesisFileRequest):
    try:
        if XTTS.model_source == "local":
          logger.info(f"Processing TTS to file with request: {request}")

        # Validate language code against supported languages.
        if request.language.lower() not in supported_languages:
             raise HTTPException(status_code=400,
                                 detail="Language code sent is either unsupported or misspelled.")

        # Now use process_tts_to_file for saving the file.
        output_file = XTTS.process_tts_to_file(
            text=request.text,
            speaker_name_or_path=request.speaker_wav,
            language=request.language.lower(),
            file_name_or_path=request.file_name_or_path  # The user-provided path to save the file is used here.
        )
        return {"message": "The audio was successfully made and stored.", "output_path": output_file}

    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

async def network_streaming_generator(request: Request, text: str, language: str, speaker_wav: str):
    aio_queue = asyncio.Queue()
    generation_complete = asyncio.Event()

    def on_audio_chunk(chunk):
        try:
            aio_queue.put_nowait(chunk)
        except asyncio.QueueFull:
            logger.warning("Network streaming queue is full, dropping audio chunk.")

    def on_generation_complete():
        generation_complete.set()

    try:
        async with engine_lock:
            speaker_wav_path = XTTS.get_speaker_wav(speaker_wav)
            engine.set_voice(speaker_wav_path)
            engine.language = language.lower()

            # Create a new stream for each request to ensure thread safety
            stream = TextToAudioStream(engine)

        # Feed the text to the stream first
        stream.feed(text)
        
        # Then start streaming
        stream.play_async(
            fast_sentence_fragment=True,
            on_audio_chunk=on_audio_chunk,
            muted=True  # Important: mute local playback for network streaming
        )

        # Yield WAV header first
        yield XTTS.get_wav_header()
        
        while stream.is_playing() or not aio_queue.empty():
            try:
                chunk = await asyncio.wait_for(aio_queue.get(), timeout=0.1)
                yield chunk
            except asyncio.TimeoutError:
                continue
                
        # Signal completion
        on_generation_complete()
               
    except Exception as e:
        logger.error(f"Error in network streaming: {e}")
        if await request.is_disconnected():
            logger.warning("Client disconnected during network streaming.")

@app.post("/tts_to_audio_stream/")
async def tts_to_audio_stream(payload: SynthesisRequest, request: Request):
    """
    Network streaming endpoint that sends audio chunks over the network as they're generated.
    This allows clients on different machines to receive and play audio in real-time.
    """
    if not (STREAM_MODE or STREAM_MODE_IMPROVE):
        raise HTTPException(status_code=400, detail="Network streaming requires STREAM_MODE or STREAM_MODE_IMPROVE to be enabled.")
    
    if payload.language.lower() not in supported_languages:
        raise HTTPException(status_code=400, detail="Language code sent is either unsupported or misspelled.")

    return StreamingResponse(network_streaming_generator(request, payload.text, payload.language, payload.speaker_wav), media_type="audio/wav")

@app.get("/debug/config")
def get_debug_config():
    """Debug endpoint to check server configuration"""
    import socket
    
    # Get server's actual IP addresses
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    return {
        "streaming_config": {
            "STREAM_MODE": STREAM_MODE,
            "STREAM_MODE_IMPROVE": STREAM_MODE_IMPROVE,
            "STREAM_PLAY_SYNC": STREAM_PLAY_SYNC,
            "streaming_enabled": bool(STREAM_MODE or STREAM_MODE_IMPROVE),
            "streaming_status": "✅ ENABLED" if (STREAM_MODE or STREAM_MODE_IMPROVE) else "❌ DISABLED"
        },
        "server_config": {
            "BASE_URL": BASE_URL,
            "DEVICE": DEVICE,
            "MODEL_VERSION": MODEL_VERSION,
            "LOWVRAM_MODE": LOWVRAM_MODE,
            "DEEPSPEED": DEEPSPEED,
            "USE_CACHE": USE_CACHE
        },
        "network_info": {
            "hostname": hostname,
            "local_ip": local_ip,
            "server_urls": [
                f"http://localhost:8020",
                f"http://127.0.0.1:8020",
                f"http://{local_ip}:8020"
            ]
        },
        "environment_variables": {
            "STREAM_MODE_IMPROVE": os.getenv("STREAM_MODE_IMPROVE"),
            "BASE_URL": os.getenv("BASE_URL"),
            "DEVICE": os.getenv("DEVICE"),
            "DEEPSPEED": os.getenv("DEEPSPEED")
        },
        "supported_languages": list(supported_languages),
        "available_endpoints": [
            "/tts_to_audio_stream/",
            "/tts_stream_realtime", 
            "/tts_to_audio/",
            "/tts_to_file",
            "/debug/config"
        ],
        "troubleshooting": {
            "streaming_error_fix": "Set STREAM_MODE_IMPROVE=true environment variable before starting server",
            "network_error_fix": "Use actual IP address instead of localhost from other computers",
            "firewall_fix": "Allow Python through Windows Firewall when prompted"
        }
    }

if __name__ == "__main__":
    # Parse host and port from BASE_URL or use defaults
    host = "0.0.0.0"  # Default to listen on all interfaces for network access
    port = 8020       # Default port
    
    if BASE_URL:
        try:
            # Parse BASE_URL (e.g., "0.0.0.0:8020" or "192.168.1.100:8020")
            if ":" in BASE_URL:
                url_host, url_port = BASE_URL.split(":")
                host = url_host if url_host else host
                port = int(url_port) if url_port else port
        except ValueError:
            logger.warning(f"Invalid BASE_URL format: {BASE_URL}. Using defaults.")
    
    # Log server configuration
    logger.info(f"Starting XTTS API Server on {host}:{port}")
    if STREAM_MODE or STREAM_MODE_IMPROVE:
        logger.info("🎵 Network streaming enabled! Audio will stream to client devices.")
        logger.info(f"📡 Network streaming endpoints:")
        logger.info(f"  - POST: http://{host}:{port}/tts_to_audio_stream/")
        logger.info(f"  - GET:  http://{host}:{port}/tts_stream_realtime")
    else:
        logger.warning("⚠️  Network streaming DISABLED. Set STREAM_MODE=true or STREAM_MODE_IMPROVE=true to enable.")
    
    uvicorn.run(app, host=host, port=port)
