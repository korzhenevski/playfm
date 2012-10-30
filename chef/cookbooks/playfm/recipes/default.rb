#
# Cookbook Name:: playfm
# Recipe:: default
#

package "libevent-dev"
package "libzmq-dev"

if node[:instance_role] == 'vagrant'
    python_virtualenv "/var/www/playfm/venv" do
      owner "vagrant"
      group "vagrant"
      action :create
    end

    python_pip "protobuf" do
      package_name "git+https://github.com/rem/python-protobuf.git"
      virtualenv "/var/www/playfm/venv"
      action :install
    end

    %w{rvlib checkfm managerfm workerfm cometfm searchfm}.each do |pkg|
      execute "#{pkg} install" do
        command "cd /var/www/playfm/#{pkg}; /var/www/playfm/venv/bin/python setup.py develop"
        action :run
      end
    end

    owner = "vagrant"
    bin_path = "/var/www/playfm/venv/bin"
else
    owner = "www-data"
    bin_path = "/var/www/playfm/current/venv/bin"
end

directory "/var/log/playfm" do
  owner owner
  group owner
  mode 0755
  action :create
end

%w{checkfm managerfm workerfm cometfm searchfm}.each do |pkg|
  supervisor_service "#{pkg}" do
    action :enable
    command "#{bin_path}/#{pkg}"
    startretries 100000
    autorestart true
    redirect_stderr true
    stdout_logfile "/var/log/playfm/#{pkg}.log"
    user owner
  end
end

template "#{node[:nginx][:dir]}/sites-available/cometfm.conf" do
  source "cometfm.conf.erb"
  owner "root"
  group "root"
  mode 0644
  notifies :reload, "service[nginx]"
end

nginx_site "cometfm.conf"
