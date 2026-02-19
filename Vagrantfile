Vagrant.configure("2") do |config|
  config.vm.box = 'digital_ocean'
  config.vm.box_url = "https://github.com/devopsgroup-io/vagrant-digitalocean/raw/master/box/digital_ocean.box"
  config.ssh.private_key_path = '~/.ssh/id_rsa'
  config.vm.synced_folder ".", "/vagrant", type: "rsync"

  config.vm.define "minitwit-server" do |server|
    server.vm.provider :digital_ocean do |provider|
    
      provider.token = ENV["DIGITAL_OCEAN_TOKEN"]
      provider.ssh_key_name = ENV["SSH_KEY_NAME"]
      
      provider.image = 'ubuntu-22-04-x64'
      provider.region = 'fra1'
      provider.size = 's-1vcpu-1gb'
    end

    server.vm.provision "shell", inline: <<-SHELL
      sudo apt-get update
      sudo apt-get install -y python3-pip sqlite3 python-is-python3
      
      
      if [ -f /vagrant/requirements.txt ]; then
        pip install -r /vagrant/requirements.txt
      fi

      # Setup the database file
      sqlite3 /tmp/minitwit.db < /vagrant/schema.sql
      
      echo "Server IP:"
      hostname -I | cut -d" " -f1
    SHELL
  end
end