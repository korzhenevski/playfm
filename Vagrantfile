# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant::Config.run do |config|
  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "base"
  config.vm.box_url = "http://files.vagrantup.com/precise64.box"
  config.vm.network :hostonly, "10.0.0.3"

  config.nfs.map_uid = Process.uid
  config.nfs.map_gid = Process.gid

  # Share an additional folder to the guest VM. The first argument is
  # an identifier, the second is the path on the guest to mount the
  # folder, and the third is the path on the host to the actual folder.
  config.vm.share_folder "v-app", "/var/www/playfm", ".", :create => true, :nfs => true
  config.vm.customize ["modifyvm", :id, "--memory", 1024]
  config.vm.provision :chef_solo do |chef|
		chef.cookbooks_path = "./cookbooks"
	
		chef.add_recipe "timezone"
		chef.add_recipe "build-essential"
		chef.add_recipe "apt"
		chef.add_recipe "vim"
		chef.add_recipe "git"
		chef.add_recipe "python"
		chef.add_recipe "nginx"
		chef.add_recipe "supervisor"
		chef.add_recipe "playfm"
    
    chef.json = {
	:vim => { extra_packages: ["vim-nox"] },
	:timezone => { value: "Europe/Moscow" },
	}
  end
end
