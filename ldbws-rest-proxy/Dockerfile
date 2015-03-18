FROM ubuntu:14.04
MAINTAINER Aled Morris <aled@wibblr.com>
RUN echo '2015-03-18' && apt-get update
RUN apt-get -y upgrade
RUN apt-get install -y python-pip
RUN pip install suds-jurko
RUN pip install flask  
RUN adduser -q --system --shell /bin/bash --disabled-password wibblr
USER wibblr
ADD ldbws-rest-proxy.py /opt/ldbws-rest-proxy.py
EXPOSE 5000 
CMD su - wibblr -c "python /opt/ldbws-rest-proxy.py"   
