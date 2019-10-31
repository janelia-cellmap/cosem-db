FROM python:3.7

RUN git clone https://github.com/janelia-cosem/sheetscrape.git
RUN pip install -r /sheetscrape/requirements.txt
RUN pip install /sheetscrape/
RUN pip install pymongo pyyaml
ADD config.yml /
ADD cosem-db-1669c2970c7f.json /
ADD dbUpdater.py /

CMD ["python", "./dbUpdater.py", "-j", "config.yml"]


