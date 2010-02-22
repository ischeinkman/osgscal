%{!?ver:	  %define ver	   0.1}
%{!?rel:	  %define rel      1}
%{!?name:	  %define name      procs_monitor}

Name:		%{name}
Version:	%{ver}
Release:	%{rel}
Summary:  A monitor that tracks information about processes

Group:		OSG Scalability
Vendor:   UCSD Physics Department
License:	MIT
URL:		  http://sourceforge.net/projects/osgscal/
Source0:	%{name}-%{version}.tgz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:  noarch

Requires:	perl

%description
This program tracks user specified processes and collects various data
such as cpu load and memory usage.

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/local/libexec/procs_monitor
mkdir -p %{buildroot}/usr/local/lib/procs_monitor
mkdir -p %{buildroot}/etc/procs_monitor
mkdir -p %{buildroot}/etc/cron.d
mkdir -p %{buildroot}/var/lib/procs_monitor

install -m 755 proc_collector.pl %{buildroot}/usr/local/libexec/procs_monitor
install -m 755 osgmon_cron.sh %{buildroot}/usr/local/libexec/procs_monitor
install -m 644 configUtils.py %{buildroot}/usr/local/lib/procs_monitor
install -m 644 plugin.py %{buildroot}/usr/local/lib/procs_monitor
install -m 644 rrdSupport.py %{buildroot}/usr/local/lib/procs_monitor
install -m 644 osgmonitoring.conf %{buildroot}/etc/procs_monitor
install -m 644 procs_to_watch.conf %{buildroot}/etc/procs_monitor
install -m 644 proc_mon.cron %{buildroot}/etc/cron.d

%postun
if [ "$1" = "0" ] ; then #Remove package
  rm -rf /var/lib/procs_monitor
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/libexec/procs_monitor/
/usr/local/lib/procs_monitor/
/etc/procs_monitor/
/etc/cron.d/proc_mon.cron
/var/lib/procs_monitor/
%doc

%changelog

