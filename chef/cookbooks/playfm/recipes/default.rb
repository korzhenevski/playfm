#
# Cookbook Name:: playfm
# Recipe:: default
#
# Copyright 2012, Example Com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

package "libevent-dev"
package "libzmq-dev"

execute "rvlib install" do
  command "cd /var/www/playfm/rvlib;
          sudo python setup.py install"
  action :run
end

directory "/var/log/playfm" do
  owner "nobody"
  group "nogroup"
  mode "0755"
  action :create
end

%w{checkfm managerfm workerfm cometfm searchfm}.each do |pkg|
  execute "#{pkg} install" do
    command "cd /var/www/playfm/#{pkg};
            sudo python setup.py develop"
    action :run
  end
  
  supervisor_service "#{pkg}" do
    action :enable
    command "/usr/local/bin/#{pkg}"
    startretries 100000
    autorestart true
    redirect_stderr true
    stdout_logfile "/var/log/playfm/#{pkg}.log"
    user "nobody"
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
