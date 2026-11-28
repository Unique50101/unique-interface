FROM python:3.12-slim
RUN useradd -m -u 1000 app
WORKDIR /home/app
RUN pip install --no-cache-dir "unique-interface @ https://files.pythonhosted.org/packages/06/18/316a9b1a75a2e01528f98245fd8615c5f3c84ecf7f5f3d480249ad2487eb/unique_interface-0.1.6-py3-none-any.whl#sha256=90e4c1f17847fe97742f5831317098ee764a5ce75c7438a19ebd33ccb0961d65"
COPY --chown=app:app app.py .
USER app
EXPOSE 7860
CMD ["python","app.py"]
