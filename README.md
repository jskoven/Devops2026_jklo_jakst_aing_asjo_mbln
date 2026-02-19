# ITU-MiniTwit Deployment

### 1. Prerequisites
* Vagrant + DigitalOcean plugin: 
  `vagrant plugin install vagrant-digitalocean`
* Secrets:
  Set your DigitalOcean credentials in your terminal:
  ```bash
  export DIGITAL_OCEAN_TOKEN="your_token"
  export SSH_KEY_NAME="your_key_name_on_digitalocean"

Note: Your private SSH key is expected to be at ~/.ssh/id_rsa


### 2. Deployment

`git clone https://github.com/jskoven/Devops2026_jklo_jakst_aing_asjo_mbln.git
cd Devops2026_jklo_jakst_aing_asjo_mbln`

`vagrant up`

`vagrant rsync`

`vagrant ssh minitwit-server -c "cd /vagrant && (nohup python minitwit.py > out.log 2>&1 &) && sleep 1`


### 3. Usage

Live App: http://161.35.68.148:5001

* Update: 
`vagrant rsync`

* Stop/Restart: 
`vagrant ssh minitwit-server -c "sudo fuser -k 5001/tcp && cd /vagrant && screen -d -m python minitwit.py"`

* Destroy VM
`vagrant destroy`
