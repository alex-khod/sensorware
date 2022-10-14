run:
	python main.py run
test:
	python -m unittest
req:
	pip install -r requirements.txt
canup:
	sudo ip link set can0 type can bitrate 500000
	sudo ip link set can0 up
candown:
	sudo ip link set can0 down
	sudo ip link del can0
	
