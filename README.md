# wrong-kind-of-snow

Server Setup
============

On a clean ubuntu 14.04 server install:

```bash
$ sudo -s
# echo xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx > ~/.ldbws-access-token
# apt-get install git nginx redis-server python-pip python-dev
# rm /etc/nginx/sites-enabled/default
# cat > /etc/nginx/sites-enabled/ldbws-rest-proxy
server {
    listen 80 default_server;
        
	location /ldbws-rest-proxy/v0.1/ {
        proxy_pass http://127.0.0.1:5001;
    }
	
	location / {
        add_header Access-Control-Allow-Origin *;
        proxy_pass http://127.0.0.1:5002;
    }
}
<ctrl-d>
# /etc/init.d/nginx restart
 * Restarting nginx nginx                                [ OK ]
# pip install suds-jurko flask redis yattag python-dateutil pytz
# exit
$ cd /opt
$ git clone https://github.com/aled/wrong-kind-of-snow
$ cd /opt/wrong-kind-of-snow
$ cd ldbws-rest-proxy && python ldbws-rest-proxy.py &
$ export LDBWS_REST_PROXY=localhost:5000
$ export REDIS_HOST=localhost
$ cd ldbws-redis-cache && ldbws-redis-cache.py &
$ export LDBWS_REST_HOST=localhost:5001
$ cd ldbws-html-generator && python ldbws-html-generator.py &
$ curl -X GET http://localhost/d/kgx
```
