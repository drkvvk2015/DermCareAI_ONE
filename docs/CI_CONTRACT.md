# DermCareAI CI Contract

The executable pull-request gate is defined in `.github/workflows/pull-request-gates.yml`.

It validates backend compilation and regression tests, rejects committed model binaries, and runs mobile TypeScript and Expo web-export smoke checks.
