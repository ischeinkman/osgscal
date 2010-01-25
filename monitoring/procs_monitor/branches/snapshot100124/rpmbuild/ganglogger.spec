Name:		procs_monitor_ganglogger
Version:	0.1
Release:	1%{?dist}
Summary:  Sends procs_monitor data to ganglia monitor

Group:		OSG Scalability
Vendor:   UCSD Physics Department
License:	MIT
URL:		  http://sourceforge.net/projects/osgscal/
Source0:	%{name}-%{version}.tgz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:  noarch

Requires:	procs_monitor python python-elementtree ganglia ganglia-gmond ganglia-gmetad

%description
This program updates ganglia monitor with data collected by the procs_monitor program

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/local/libexec/procs_monitor
mkdir -p %{buildroot}/etc/procs_monitor

install -m 755 ganglogger.py %{buildroot}/usr/local/libexec/procs_monitor
install -m 644 ganglogger.conf %{buildroot}/etc/procs_monitor

%post

if [ "$1" = "1" ] ; then #First install
  echo "/usr/local/libexec/procs_monitor/ganglogger.py -t 1800 /etc/procs_monitor/ganglogger.conf" >> /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%preun
if [ "$1" = "0" ] ; then #Remove package
  sed -e '/ganglogger/d' -i /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/libexec/procs_monitor/ganglogger.py*
/etc/procs_monitor/ganglogger.conf
%doc

%changelog

