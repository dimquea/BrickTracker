# Quickstart

> **Note**
> The following page is based on version `1.2.0` of BrickTracker.

## Prerequisites
- Docker and Docker Compose installed
- No API key: catalog data comes from a downloadable archive. It has to be fetched once from the admin page after the first start, see [the BrickLink catalog](bricklink-catalog.md)
- curl or wget (for downloading configuration files)

## Note on Environment Configuration
BrickTracker can be configured using either:
- A `.env` file (recommended and shown in this guide)
- Environment variables in compose.yaml

This guide uses the `.env` file approach for better maintainability. The environment variables in the compose.yaml file are kept minimal and only reference the essential paths.

## Directory Setup

1. Create the project directory and structure:
```bash
mkdir -p bricktracker/{data,static/{instructions,minifigures,parts,sets}}
cd bricktracker
```

2. Download the sample configuration files:
```bash
# Get the environment file template
curl -o env.sample https://raw.githubusercontent.com/FrederikBaerentsen/BrickTracker/main/env.sample

# Or with wget:
# wget -O env.sample https://raw.githubusercontent.com/FrederikBaerentsen/BrickTracker/main/env.sample
```

## Docker Compose Configuration

Create `compose.yaml` with this content:
```yaml
services:
  bricktracker:
    container_name: BrickTracker
    restart: unless-stopped
    image: gitea.baerentsen.space/frederikbaerentsen/bricktracker:1.2.0
    ports:
      - "3333:3333"
    volumes:
      - ./data:/data
      - ./static/instructions:/app/static/instructions
      - ./static/minifigures:/app/static/minifigures
      - ./static/parts:/app/static/parts
      - ./static/sets:/app/static/sets
    env_file: ".env"
```

## Starting BrickTracker

1. Start the application:
```bash
docker compose up -d
```

2. Access BrickTracker at `http://localhost:3333`

Please refer to [Environment Variables Reference](env.md) for a list of available variables.

3. Read more in [First steps](first-steps.md)

## Troubleshooting

1. If the application won't start:
   - Check if port 3333 is available
   - Check logs with `docker compose logs -f`
   - Ensure `.env` file is properly formatted

2. If images aren't appearing:
   - Verify write permissions on static directories
   - Ensure network connectivity to GitHub, where the catalog archive is published

3. If you can't add sets:
   - Verify the catalog has been downloaded (Admin → Themes)
   - Check the application logs for API errors

4. Environment configuration issues:
   - Make sure `.env` file exists and is readable
   - Check for any syntax errors in `.env` file
   - Verify no conflicting environment variables are set in the shell

For more troubleshooting, take a look at [Common Errors](common-errors.md)

Please refer to [Setup](setup.md) for more information.