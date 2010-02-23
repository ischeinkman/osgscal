%{!?ver:          %define ver      0.1}
%{!?rel:          %define rel      1}
%{!?name:         %define name      procs_monitor_zablogger}

Name:           %{name}
Version:        %{ver}
Release:        %{rel}
Summary:  Sends procs_monitor data to zabbix monitor

Group:		OSG Scalability
Vendor:   UCSD Physics Department
License:	MIT
URL:		  http://sourceforge.net/projects/osgscal/
Source0:	%{name}-%{version}.tgz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:  noarch

Requires:	procs_monitor python python-elementtree zabbix zabbix-agent

%description
This program updates zabbix monitor with data collected by the procs_monitor program

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/local/libexec/procs_monitor
mkdir -p %{buildroot}/etc/procs_monitor

install -m 755 zablogger.py %{buildroot}/usr/local/libexec/procs_monitor
install -m 644 zablogger.conf %{buildroot}/etc/procs_monitor

%post

if [ "$1" = "1" ] ; then #First install
  echo "/usr/local/libexec/procs_monitor/zablogger.py -t 1800 /etc/procs_monitor/zablogger.conf" >> /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%preun
if [ "$1" = "0" ] ; then #Remove package
  sed -e '/zablogger/d' -i /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/libexec/procs_monitor/zablogger.py*
/etc/procs_monitor/zablogger.conf
%doc LICENSE

%changelog

