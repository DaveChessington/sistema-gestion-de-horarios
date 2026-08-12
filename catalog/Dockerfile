FROM python:3.13-slim
WORKDIR /app
COPY . /app
ADD run.py ./
RUN pip install -r requirements.txt
CMD ["python", "run.py"]

#build -> docker build -t gestion-horarios .
#run -> docker run -d -p 5000:5000 --name gestion-horarios gestion-horarios