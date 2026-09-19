# DermCareAI CI Contract

The executable pull-request gates validate backend compilation and regression tests, reject committed model binaries, and run mobile TypeScript and Expo web-export smoke checks.

The recovery/integration workflow uses the backend working directory with `PYTHONPATH=.` so local backend modules resolve correctly.
