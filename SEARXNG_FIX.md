# SearxNG Search Fix

## Problem
The application is experiencing search failures with the error:
```
Searxng search failed. did you run start_services.sh? is docker still running?
```

This happens because:
1. The external SearxNG instance at `https://searx.be` is returning 403 Forbidden
2. No local SearxNG instance is running
3. Docker is not running or not configured

## Solution

### Quick Fix (Recommended)
Use the new startup script that includes local SearxNG:

```bash
./start_with_searxng.sh
```

This script will:
1. Check if Docker is installed and running
2. Start a local SearxNG container
3. Update your `.env` file to use the local instance
4. Start the backend and frontend services

### Manual Fix

1. **Start Docker** (if not running):
   ```bash
   # On macOS:
   open -a Docker
   
   # Or start Docker Desktop manually
   ```

2. **Start local SearxNG**:
   ```bash
   docker-compose up -d searxng
   ```

3. **Update .env file**:
   Change the line:
   ```
   SEARXNG_BASE_URL=https://searx.be
   ```
   To:
   ```
   SEARXNG_BASE_URL=http://localhost:8080
   ```

4. **Restart your application**:
   ```bash
   ./start.sh
   ```

### Alternative SearxNG Instances
If you prefer to use a public SearxNG instance instead of running locally, you can update your `.env` file with one of these:

- `SEARXNG_BASE_URL=https://searx.tiekoetter.com`
- `SEARXNG_BASE_URL=https://search.sapti.me`
- `SEARXNG_BASE_URL=https://searx.work`

**Note**: Public instances may also have rate limiting or availability issues.

### Verify the Fix

1. **Check SearxNG is running**:
   ```bash
   docker ps
   ```
   You should see a `searxng` container running.

2. **Test the search**:
   - Open your browser to `http://localhost:8080`
   - Try a search query
   - Or test from your application

3. **Check logs if issues persist**:
   ```bash
   docker logs searxng
   ```

## Files Created

- `docker-compose.yml` - Docker Compose configuration for SearxNG
- `searxng-settings.yml` - SearxNG configuration optimized for local development
- `start_with_searxng.sh` - Enhanced startup script with SearxNG support
- Updated `sources/tools/searxSearch.py` - Better error handling and user guidance

## Troubleshooting

### Docker Issues
- **Docker not installed**: Download from https://docs.docker.com/get-docker/
- **Docker daemon not running**: Start Docker Desktop or run `open -a Docker`
- **Permission denied**: Add your user to the docker group or use sudo

### SearxNG Issues
- **Container won't start**: Check Docker logs with `docker logs searxng`
- **Search still fails**: Verify the URL in `.env` file matches your setup
- **Port conflicts**: Change port in `docker-compose.yml` if 8080 is already in use

### Application Issues
- **Backend won't start**: Check if port 7777 is available
- **Frontend won't start**: Check if port 3000 is available and Node.js is installed
- **Search errors persist**: The updated error messages will provide more specific guidance

## Next Steps

Once everything is working, you can:
1. Customize SearxNG settings in `searxng-settings.yml`
2. Add more search engines or configure existing ones
3. Set up monitoring for the services
4. Configure SSL if needed for production use