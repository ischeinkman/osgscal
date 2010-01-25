Name:		procs_monitor_syslogger
Version:	0.1
Release:	1%{?dist}
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
This program uses syslog to log information collected by the procs_monitor program

%prep
%setup -q

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/usr/local/libexec/procs_monitor
#mkdir -p %{buildroot}/usr/local/lib/procs_monitor
#mkdir -p %{buildroot}/etc/procs_monitor
#mkdir -p %{buildroot}/etc/cron.d
mkdir -p %{buildroot}/etc/logrotate.d
#mkdir -p %{buildroot}/var/lib/procs_monitor

install -m 755 syslogger.py %{buildroot}/usr/local/libexec/procs_monitor
install -m 644 osg_log_rotate %{buildroot}/etc/logrotate.d/osgmonitoring
#install -m 755 osgmon_cron.sh %{buildroot}/usr/local/libexec/procs_monitor
#install -m 644 configUtils.py %{buildroot}/usr/local/lib/procs_monitor
#install -m 644 plugin.py %{buildroot}/usr/local/lib/procs_monitor
#install -m 644 rrdSupport.py %{buildroot}/usr/local/lib/procs_monitor
#install -m 644 osgmonitoring.conf %{buildroot}/etc/procs_monitor
#install -m 644 procs_to_watch.conf %{buildroot}/etc/procs_monitor
#install -m 644 proc_mon.cron %{buildroot}/etc/cron.d

%post

if [ "$1" = "1" ] ; then #First install
for i in  `seq 0 7` 
   do line="`grep -E "local$i" /etc/syslog.conf`"
   if [ -z "$line" ] 
      then
      echo "local$i.*						/var/log/osgmonitoring.log" >>/etc/syslog.conf 
      echo "/usr/local/libexec/procs_monitor/syslogger.py -s $i -t 1800 /var/lib/procs_monitor/osgmonitoring.xml" >> /usr/local/libexec/procs_monitor/osgmon_cron.sh
      service syslog  restart
      break
   fi
done
fi
if [ "$1" = "2" ] ; then #Update
#remove in case it was there...
sed -e '/local[0-7].*\/var\/log\/osgmonitoring.*log.*/d' -i /etc/syslog.conf
sed -e '/syslogger/d' -i /usr/local/libexec/procs_monitor/osgmon_cron.sh
for i in  `seq 0 7` 
   do line="`grep -E "local$i" /etc/syslog.conf`"
   if [ -z "$line" ] 
      then
      echo "local$i.*						/var/log/osgmonitoring.log" >>/etc/syslog.conf 
      echo "/usr/local/libexec/procs_monitor/syslogger.py -s $i -t 1800 /var/lib/procs_monitor/osgmonitoring.xml" >> /usr/local/libexec/procs_monitor/osgmon_cron.sh
      service syslog  restart
      break
   fi
done
fi

%preun
if [ "$1" = "0" ] ; then #Remove package
sed -e '/local[0-7].*\/var\/log\/osgmonitoring.*log.*/d' -i /etc/syslog.conf
sed -e '/syslogger/d' -i /usr/local/libexec/procs_monitor/osgmon_cron.sh
service syslog  restart
fi

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/usr/local/libexec/procs_monitor/syslogger.py*
/etc/logrotate.d/osgmonitoring
%doc

%changelog

