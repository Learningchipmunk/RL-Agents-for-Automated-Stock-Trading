sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt upgrade -y
sudo apt install python3.7 python3.7-dev python3.7-venv
python3.7 -m venv rl_env
source rl_env/bin/activate
pip install -r requirements.txt
pip install git+https://github.com/AI4Finance-LLC/FinRL-Library.git