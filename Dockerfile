# this dockerfile is used to build the image

# Use this python for setup
FROM python:3.14-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Tell Docker that this container listens on port 8000
EXPOSE 8000

# Command to run the application
CMD [ "uvicorn", "src.core.main:app", "--host", "0.0.0", "--port", "8000" ]