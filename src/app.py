import json
import os
import time
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# from instalily.logging import logger
import redis
from ddtrace import tracer

#
app = FastAPI()

redis_host = os.environ.get("REDISHOST", "localhost")
redis_port = int(os.environ.get("REDISPORT", 6379))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port)
# redis_client = redis.Redis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=0, protocol=3)
PROJECT = os.getenv("SERVICE")

# origins = ["*"]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


def gcr_corr(request: Request) -> str:
    trace_header = request.headers.get("X-Cloud-Trace-Context")
    if trace_header and PROJECT:
        trace = trace_header.split("/")
        return f"logging.googleapis.com/trace : projects/{PROJECT}/traces/{trace[0]}"
    else:
        return ""


# Custom exception handler for all exceptions
@app.exception_handler(Exception)
@tracer.wrap()
async def custom_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred."},
    )


# Handler for validation exceptions
@app.exception_handler(exc_class_or_status_code=RequestValidationError)
@tracer.wrap()
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    gc: str = gcr_corr(request=request)
    ""
    # logger.warning(f"Validation error: {exc.errors()} – {gc}")

    return JSONResponse(
        status_code=422,
        content={"message": "Validation error", "details": exc.errors(), "gc": gc},
    )


# Middleware to log requests and responses
@app.middleware("http")
@tracer.wrap()
async def log_requests(request: Request, call_next):
    body: bytes = await request.body()
    # logger.info(f"Request: {request.method} {request.url} – body: {body}")
    print(f"Request: {request.method} {request.url} – body: {body}")
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    formatted_process_time = f"{process_time:.2f}s"
    print(
        f"Response status: {response.status_code} completed in {formatted_process_time}"
    )

    return response


@app.get("/")
async def root():
    my_user = "momothain"

    log_dict: dict = {
        "user": my_user,
        "metadata": "this is the root endpoint",
        "note": "the instalily logging package will insert the runtime code flow and datadog attributes",
        "attr": "these are all (Standard) Attributes that can be encoded in datadog, automatically extracted, and aggregated in a Log Pipeline",
    }
    log_dict_str: str = json.dumps(log_dict, indent=4)

    # logger.info(log_dict_str)
    # logger.error(log_dict)  # TODO: test
    r = JSONResponse(log_dict)
    print(r)
    return r


@app.get(path="/error")
async def error():
    return 1 / 0  # divby0 err

    """_summary_
    TODO: BROKEN?
    Returns:
        _type_: _description_
    """


@app.post(path="/echo")
async def echo(req: Request) -> Response:
    return JSONResponse(
        {"msg": "Echoing request body", "request_body": req.body(), "rawr": req}
    )
