#!/bin/bash

if [ ! -d "venv3" ]; then
  python3 -m venv venv3
fi

. venv3/bin/activate
pip install -r requirements

sed -i -e 's/wss:\/\/api.quedex.net/ws:\/\/localhost:8080/g' examples/simple_trading.py

python -m unittest discover end_to_end_tests &
TESTS_PID=$!

while ! nc -z localhost 8080; do
  sleep 0.2
done

PYTHONPATH=".:.." python examples/simple_trading.py &
CLIENT_PID=$!

wait $TESTS_PID
TESTS_RESULT=$?

kill $CLIENT_PID

sed -i -e 's/ws:\/\/localhost:8080/wss:\/\/api.quedex.net/g' examples/simple_trading.py

exit $TESTS_RESULT

deactivate
