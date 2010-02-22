%{!?ver:          %define ver      0.1}
%{!?rel:          %define rel      1}
%{!?name:         %define name      procs_monitor_txtlogger}

Name:           %{name}
Version:        %{ver}
Release:        %{rel}
Summary:  Logs procs_monitor data

Group:		OSG Scalability
Vendor:   UCSD Physics Department
License:	MIT
URL:		  http://sourceforge.net/projects/osgscal/
Source0:	%{name}-%{version}.tgz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root
BuildArch:  noarch

Requires:	procs_monitor python python-elementtree

%description
This program logs information collected by procs_monitor and writes to ordinary
text files

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/local/libexec/procs_monitor
install -m 755 txtlogger.py %{buildroot}/usr/local/libexec/procs_monitor

%post

if [ "$1" = "1" ] ; then #First install
  echo "/usr/local/libexec/procs_monitor/txtlogger.py -t 1800 /var/lib/procs_monitor/osgmonitoring.xml /var/lib/procs_monitor/procs" >> /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%preun
if [ "$1" = "0" ] ; then #Remove package
  sed -e '/txtlogger/d' -i /usr/local/libexec/procs_monitor/osgmon_cron.sh
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/libexec/procs_monitor/txtlogger.py*
%doc

%changelog

