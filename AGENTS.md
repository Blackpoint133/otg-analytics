# Staging runtime validation

For executable application changes under `streamlit_opensea_sales/`, focused tests, compile/pip/diff checks, and a deliberate restart through `ops/staging/restart_staging.ps1` are mandatory before reporting PASS. Use the staging virtual environment, confirm the new PID and ExpectedHead, run application import/runtime smoke checks, and verify no Streamlit application exception is present.

HTTP 200 alone is not application-health proof. Do not rely on Streamlit hot reload as final validation. The staging restart script is never for production; port 8502 and the protected main branch remain untouched unless deployment is explicitly authorized.
