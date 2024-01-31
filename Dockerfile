FROM python:3.12.1
WORKDIR /app.py
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
ENTRYPOINT ["streamlit", "run", "app.py"]
