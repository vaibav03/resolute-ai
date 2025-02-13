# Use official Python 3 image
FROM python:3

ENV PYTHONUNBUFFERED=1  
WORKDIR /app  
COPY requirements.txt /app/ 
RUN pip install --upgrade pip  
RUN pip install -r requirements.txt  
COPY . /app  

EXPOSE 3000  

CMD   ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
