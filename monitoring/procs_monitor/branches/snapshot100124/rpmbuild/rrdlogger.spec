Name:		procs_monitor_rrdlogger
Version:	0.1
Release:	1%{?dist}
Summary:  Writes procs_monitor data to rrd databases

Group:		OSG Scalability
Vendor:   UCSD Physics Department
License:	MIT
URL:		  http://sourceforge.net/projects/osgscal/
Source0:	%{name}-%{version}.tgz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:  noarch

Requires:	procs_monitor python python-elementtree rrdtool rrdtool-python

%description
This program updates rrd databases with data collected by the procs_monitor program

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/local/libexec/procs_monitor
mkdir -p %{buildroot}/etc/procs_monitor

install -m 755 rrdlogger.py %{buildroot}/usr/local/libexec/procs_monitor
install -m 644 rrdlogger.conf %{buildroot}/etc/procs_monitor

%post

if [ "$1" = "1" ] ; then #First install
  echo "/usr/local/libexec/procs_monitor/rrdlogger.py -t 1800 /etc/procs_monitor/rrdlogger.conf" >> /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%preun
if [ "$1" = "0" ] ; then #Remove package
  sed -e '/rrdlogger/d' -i /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/libexec/procs_monitor/rrdlogger.py*
/etc/procs_monitor/rrdlogger.conf
%doc

%changelog

