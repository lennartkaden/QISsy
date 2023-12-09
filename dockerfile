# using python-runtime-images
FROM python:3.10

# set workdir
WORKDIR /app

# install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy code into container
COPY . .

# copy the config content into the config.json file
ARG CONFIG_CONTENT
RUN echo "$CONFIG_CONTENT" > config.json

# expose port 8000
EXPOSE 8000

# command to start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
