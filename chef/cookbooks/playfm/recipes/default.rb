#
# Cookbook Name:: playfm
# Recipe:: default
#

package "libevent-dev"
package "libzmq-dev"

if node[:instance_role] == 'vagrant'
    owner = "vagrant"
    bin_path = "/usr/local/bin"

    %w{rvlib checkfm managerfm workerfm cometfm searchfm}.each do |pkg|
      execute "#{pkg} install" do
        command "cd /var/www/playfm/#{pkg}; python setup.py develop"
        action :run
      end
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
        stopsignal "INT"
      end
    end
else
    owner = "www-data"
    bin_path = "/var/www/playfm/current/venv/bin"

    directory "/var/www/playfm/conf" do
      owner owner
      group owner
      mode 0755
      action :create
    end

    %w{checkfm managerfm workerfm cometfm searchfm}.each do |pkg|
      template "/var/www/playfm/conf/#{pkg}.conf" do
        source "#{pkg}.conf.erb"
        owner owner
        group owner
        mode 0644
      end
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
        command "#{bin_path}/#{pkg} /var/www/playfm/conf/#{pkg}.conf"
        startretries 100000
        autorestart true
        redirect_stderr true
        stdout_logfile "/var/log/playfm/#{pkg}.log"
        user owner
        stopsignal "INT"
      end
    end
end

template "#{node[:nginx][:dir]}/sites-available/playfm.conf" do
  source "nginx.conf.erb"
  owner "root"
  group "root"
  mode 0644
  notifies :reload, "service[nginx]"
end

nginx_site "playfm.conf"
