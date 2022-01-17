# RL-Project - Stock Trading
​		A **Reproducibility Study** of Hongyang Yang et al. [paper](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3690996).

### Prerequisites

1. **python 3.7**
2. **ubuntu** or **WSL**

### How to Setup

You'll need to install `python 3.7` to use our code. Below you'll find a way to install `python 3.7` with `venv`. This will allow you to create a specified virtual environment for this project called `rl_env`.

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt upgrade -y
sudo apt install python3.7 python3.7-dev python3.7-venv
sudo apt install libopenmpi-dev
python3 -m venv rl_env
source rl_env/bin/activate
```

When you are finished, you can now install the required python libraries for this project:

```bash
pip install -r requirements.txt
pip install git+https://github.com/AI4Finance-LLC/FinRL-Library.git
```

​	:warning:`FinRL` only works on ubuntu like systems.:warning:

### How to run the script

The file `auteurs.json` in the folder `configs` has all the parameters used in the original experiment of the paper. To run it you must copy the command below:

```bash
python3 preprocessandtrainenv.py --ConfigName=auteurs
```

### Different trading environments

It is possible to run the algorithms on the following stock groups: dow_30, nas_100, sp_500, faang, crypto (BTC, ETH, LTC, BCH Vs USD), memes (ETH, LTC, BCH, DOGE, SHIB, UNI3 Vs BTC).

### Authors

[Jean-Charles LAYOUN](https://www.linkedin.com/in/JClayoun). Can be contacted at [jean-charles.layoun@polytechnique.edu](mailto:jean-charles.layoun@polytechnique.edu).
[Alexis ROGET](https://www.linkedin.com/in/alexisroger99/). Can be contacted at [alexis.roger@umontreal.ca](mailto:alexis.roger@umontreal.ca).

