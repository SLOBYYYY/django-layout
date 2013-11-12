# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "base"

  config.vm.network :forwarded_port, guest: 8000, host: 8111

  config.vm.network :private_network, ip: "1.1.1.2"

  config.vm.synced_folder ".", "/home/vagrant/{{ project_name }}"

  config.vm.provision :shell, :path => "provision/install.sh", :args => "{{ project_name }}"
end
