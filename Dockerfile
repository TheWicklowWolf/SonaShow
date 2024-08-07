FROM python:3.12-alpine

# Set build arguments
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}

# Create User
ARG UID=1000
ARG GID=1000
RUN addgroup -g $GID general_user && \
    adduser -D -u $UID -G general_user -s /bin/sh general_user

# Create directories and set permissions
COPY . /sonashow
WORKDIR /sonashow
RUN chown -R $UID:$GID /sonashow

# Install requirements and run code as general_user
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
USER general_user
CMD ["gunicorn", "src.SonaShow:app", "-c", "gunicorn_config.py"]
