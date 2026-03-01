# Python image to use.
FROM python:3.11-alpine

RUN apk update
RUN apk add chromium chromium-chromedriver

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set the working directory to /app
WORKDIR /app

# Install dependencies from lockfile before copying source for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the working directory contents into the container at /app
COPY . .

# Add the venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run app.py when the container launches
ENTRYPOINT ["python", "src/app.py"]
