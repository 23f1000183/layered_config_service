# Layered Configuration FastAPI service

## Deploy
Deploy this folder as a Python web service (for example, on Render). The `render.yaml`
is included as a starting point. Set OS-level environment variables `APP_PORT=8498`
and `APP_LOG_LEVEL=debug` in the deployment dashboard as well. The platform's own
`PORT` variable is used by Uvicorn to bind the HTTP server; `APP_PORT` is the application
configuration value returned by `/effective-config`.

Build command:
`pip install -r requirements.txt`

Start command:
`uvicorn main:app --host 0.0.0.0 --port $PORT`

## Test
`/effective-config?set=port=9000&set=debug=true`
Repeated `set` parameters are supported. The `api_key` is always masked.
