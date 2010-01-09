#!/usr/bin/perl -w
#
# proc_collector.pl
# 
# Description:
#   Collect load and process info and parse to xml file
#
# Usage:
#   proc_collector.pl CONFIG-FILE
#
# Author:
#   Jeff Dost (Sept 2009) derived from osgmonitoring.pl
#   from osgmonitoring.rpm created by Toni Coarasa (2008)
#
 
use strict;
#use Sys::Hostname;
#use CGI qw(:standard);
#use DBI;
use Sys::Syslog qw(:DEFAULT setlogsock);
use File::CheckTree;
use POSIX qw(strftime);
use Time::Local;
use File::Copy;
use File::Basename;

###############
#
# Subroutines
#
###############

sub getUpdateTime
{
  my $now = time;
  my @localtime = localtime($now);
  my @gmtime = gmtime($now);
  my $offset = timegm(@localtime) - $now;
  my $mag = abs($offset);
  my %updateTime;
  $updateTime{'local'}{'iso8601'} = strftime("%Y-%m-%dT%H:%M:%S", @localtime);
  $updateTime{'local'}{'iso8601'} .= sprintf "%+03i:%02i", $offset / $mag * int($mag / 3600), int($mag % 3600 / 60);
  $updateTime{'local'}{'rfc2822'} = strftime("%a, %d %b %Y %H:%M:%S ", @localtime);
  $updateTime{'local'}{'rfc2822'} .= sprintf "%+03i%02i", $offset / $mag * int($mag / 3600), int($mag % 3600 / 60);
  $updateTime{'local'}{'human'} = strftime("%a %b %d %H:%M:%S %Y", @localtime);
  $updateTime{'utc'}{'iso8601'} = strftime("%Y-%m-%dT%H:%M:%SZ", @gmtime);
  $updateTime{'utc'}{'rfc2822'} = strftime("%a, %d %b %Y %H:%M:%S +0000", @gmtime);
  $updateTime{'utc'}{'unix'} = $now;

  return \%updateTime;
}

sub GetProcInfo
{
  my ($DBprocessname, $ProcRegExp, $ps, $lsof) = @_;

  my @INFOPROCS= () ;

  #call ps and collect output
  @INFOPROCS=`$ps -eo pid,user,rtprio,nice,vsize,rss,share,s,pcpu,pmem,cputime,ppid,command`;   
  # ps -eo pid,user,rtprio,nice,vsize,rss,share,s,pcpu,pmem,cputime,ppid,command |head -1
  #  PID USER     RTPRIO  NI    VSZ   RSS - S %CPU %MEM     TIME  PPID COMMAND
  #Let's get the command we are interested in (the 12th column)
  #INFO contains the lines with the information
  die "Problem getting the ps output for $DBprocessname\n" if $#INFOPROCS < 0;

  # get lines that match process we want
  my @INFO = grep ( /^ *([^ ]+ +){12}$ProcRegExp$/, @INFOPROCS);  

  my $ProcIDs;
  my ($PCPU,$PMEM,$RSS,$VSIZE,$NumberOfProcs,$NumberOfOpenFiles)= ( 0 , 0 , 0 , 0 , 0 ,0 );

  # collect process data
  if ( $#INFO >= 0 )
  {
    foreach my $line (@INFO)		
    {
      # parse values from each column of ps output
      my ($pid,$user,$rtprio,$nice,$vsize,$rss,$share,$s,$pcpu,$pmem,$cputime,$ppid,$command) = 
      split(' ',$line); #Notice the use of ' ' and not /\s+/. This drops the starting \s  

      #Let's do the math	 
      # build list of all pids belonging to process       
      if ($NumberOfProcs > 0) 
      {
        $ProcIDs=$pid.",".$ProcIDs;
      } 
      else 
      {
        $ProcIDs=$pid;	 
      }

      # accumulate values of each pid to total values of process
      $NumberOfProcs++;      
      $PCPU+=$pcpu;      
      $PMEM+=$pmem;      
      $RSS+=$rss;      
      $VSIZE+=$vsize; 
    }

    # collect number of files open by each pid
    my @OpenFilesOutput =`$lsof -p $ProcIDs`;   
    die "Problem getting the lsof output for $DBprocessname\n" if $#OpenFilesOutput < 0;
    
    $NumberOfOpenFiles=$#OpenFilesOutput-1;   
  }

  # return hash containing collected data
  return {name => $DBprocessname, pcpu => $PCPU, pmem => $PMEM, vsize => $VSIZE, 
    rss => $RSS, procs => $NumberOfProcs, files => $NumberOfOpenFiles};
}

sub getTopInfo
{
  my $top = shift @_;
  my @lines = `$top -b -n 2`; # -n 2 because cpu info from first step is inaccurate
  die "Problem getting top output\n" if $#lines < 0;
#foreach my $line (@lines) {
#  print $line;
#}
  # remove output of first top interval
  shift @lines;

  my $length = $#lines + 1;

  for (my $i = 0; $i < $length; $i++)
  {
    last if $lines[0] =~ /^top/;
    shift @lines;
  }  

  my %values;

  $_ = $lines[0];
  s/:/ /g;
  s/,/ /g;
  my @loads = split /\s+/;
  $values{'loadavg'}{15} = pop @loads;
  $values{'loadavg'}{5} = pop @loads;
  $values{'loadavg'}{1} = pop @loads;

  $lines[1] =~ /(\d+)/;
  $values{'procs_tot'} = $1;

  $_ = $lines[2];
  s/Cpu\(s\):\s*//;
  s/%..//g;
  my @cpuvals = split(/,\s*/);

  $values{'user'} = $cpuvals[0];
  $values{'sys'} = $cpuvals[1];
  $values{'idle'} = $cpuvals[3];
  $values{'wait'} = $cpuvals[4];

  return \%values;
}

# translate special xml characters first!
# print xml output file
sub genXML
{
  my($topVals, $processes, $error) = @_;  

  unless (defined $topVals)
  {
    $topVals = {'loadavg' => {1 => '',
                              5 => '',
                              15 => '',
                             },
              
                'user' => '',
                'sys' => '',
                'idle' => '',
                'wait' => '',
                'procs_tot' => '',
               };
  }

  $error = '' unless defined $error;
  my $flag = $error ? 'true' : 'false';
  my $updateTime = getUpdateTime();
  my $output = <<EOF;
<?xml version="1.0"?>
<stats>
  <updated>
    <timezone name="Local" ISO8601="$updateTime->{'local'}{'iso8601'}" RFC2822="$updateTime->{'local'}{'rfc2822'}" human="$updateTime->{'local'}{'human'}"/>
    <timezone name="UTC" ISO8601="$updateTime->{'utc'}{'iso8601'}" RFC2822="$updateTime->{'utc'}{'rfc2822'}" unixtime="$updateTime->{'utc'}{'unix'}"/>
  </updated>
  <error>
    <flag>$flag</flag>
    <message>$error</message>
  </error>
  <cpu>
    <loadavg min="1">$topVals->{'loadavg'}{1}</loadavg>
    <loadavg min="5">$topVals->{'loadavg'}{5}</loadavg>
    <loadavg min="15">$topVals->{'loadavg'}{15}</loadavg>
    <user>$topVals->{'user'}</user>
    <sys>$topVals->{'sys'}</sys>
    <idle>$topVals->{'idle'}</idle>
    <wait>$topVals->{'wait'}</wait>
  </cpu>
  <processes>
    <procs_tot>$topVals->{'procs_tot'}</procs_tot>
EOF

  foreach my $proc (@{$processes}) 
  {
    $output .= <<EOF;
    <process name="$proc->{'name'}">
      <pcpu>$proc->{'pcpu'}</pcpu>
      <pmem>$proc->{'pmem'}</pmem>
      <vsize>$proc->{'vsize'}</vsize>
      <rss>$proc->{'rss'}</rss>
      <procs>$proc->{'procs'}</procs>
      <files>$proc->{'files'}</files>
    </process>
EOF
  }

  $output .= <<EOF;
  </processes>
</stats>
EOF
  return $output;
}

################
#
#   Main
#
################

# this script requires a command line argument that specifies the osgmonitoring.conf file location
die "Usage: $0 CONFIG-FILE\n" if $#ARGV < 0;
my $ConfigurationFile = $ARGV[0];

# to store values parsed from config file
my %ConfigurationData;
$ConfigurationData{'procs_conf'}{'filter'}='.+';
$ConfigurationData{'out_file'}{'filter'}='.+';
#$ConfigurationData{'syslogFacility'}{'filter'}='local[0-7]';
$ConfigurationData{'ExecutableFile_ps'}{'filter'}='.+';
$ConfigurationData{'ExecutableFile_lsof'}{'filter'}='.+';
$ConfigurationData{'ExecutableFile_top'}{'filter'}='.+';

#Let's Read the configuration information
open(my $Conf, "<", "$ConfigurationFile") or die "Can't read file $ConfigurationFile \n";
while (<$Conf>)
{
  chomp;                  # no newline
  s/#.*//;               # no comments
  s/^\s+//;               # no leading white
  s/\s+$//;               # no trailing white
  next unless length;     # anything left?

  # make sure the line is of the form field1 = field2, with arbitrary number of
  # whitespaces allowed between the = sign
  if ( $_ =~ /^([^ ]+) *= *([^ ]+.*)$/ )
  {
    my $variable=$1;
    my $value=$2;
    # check if it's a known variable and set it's value if valid
    if ( exists $ConfigurationData{$variable} && $ConfigurationData{$variable}{'filter'} )
    {
      my $filter=$ConfigurationData{$variable}{'filter'};

      if ( $value=~/^$filter$/ )
      {
        $ConfigurationData{$variable}{'value'}="$value";     
      }     
    }
  }
}

close $Conf;

# if not defined in config file set some defaults
unless (defined ($ConfigurationData{'ExecutableFile_ps'}{'value'}))
{
  $ConfigurationData{'ExecutableFile_ps'}{'value'} = '/bin/ps';
}

unless (defined ($ConfigurationData{'ExecutableFile_lsof'}{'value'}))
{
  $ConfigurationData{'ExecutableFile_lsof'}{'value'} = '/usr/sbin/lsof';
}

unless (defined ($ConfigurationData{'ExecutableFile_top'}{'value'}))
{
  $ConfigurationData{'ExecutableFile_top'}{'value'} = '/usr/bin/top';
}

my $dirname = dirname $0;
unless (defined ($ConfigurationData{'procs_conf'}{'value'}))
{
  $ConfigurationData{'procs_conf'}{'value'} = "$dirname/../etc/procs_to_watch.conf";
}

unless (defined ($ConfigurationData{'out_file'}{'value'}))
{
  $ConfigurationData{'out_file'}{'value'} = "$dirname/../osgmonitoring.xml";
}

#Check All Our Variables Were Read
my @ConfigurationDataVariables = keys(%ConfigurationData);
foreach my $key ( @ConfigurationDataVariables )
{
  unless ( $ConfigurationData{$key}{'value'} )
  {
    die "Error! Could not read properly a value for $key\nCheck the value in the configuration file: $ConfigurationFile\n";
  }
}

# prepare filehandle for writing xml file

my $tmpout = $ConfigurationData{'out_file'}{'value'} . ".tmp";
open(my $OUT, ">", $tmpout) or die "Can't read file $tmpout \n";

my $topVals;
#Check ps lsof and top are there
my @files=grep ( /^ExecutableFile_/, (keys %ConfigurationData) );
my $IN;
eval
{
  foreach my $checkfile (@files)
  {
    validate( "$ConfigurationData{$checkfile}{'value'}".q{  -erx || die "$file not there or not readable or not executable\n" });
  }

  # collect top values
  $topVals = getTopInfo($ConfigurationData{'ExecutableFile_top'}{'value'});

#Let's open the file and do one at a time  
# prepare filehandle for reading 'process to watch' config file
  open($IN, "<", "$ConfigurationData{'procs_conf'}{'value'}") or die 
    "Can't read file $ConfigurationData{'procs_conf'}{'value'}\n";
};
if ($@)
{
  chomp($@);
  print $OUT genXML($topVals, [],  $@);
  close($OUT);
  copy($tmpout, $ConfigurationData{'out_file'}{'value'}) || die "Copy failed: $!";
  unlink($tmpout);
  exit 1;
}

# 2 element array to store fields for each line of 'procs to watch' file
my @line = (); 

# store info about each process in array
my @processes;

#ps will be called every time GetProcInfo is, shouldn't it just be called once?
eval
{
  while (<$IN>)
  {
    chomp;                  # no newline
    s/^#.*//;               # no comments
    s/^\s+//;               # no leading white
    s/\s+$//;               # no trailing white
    next unless length;     # anything left?

    @line=split(",",$_);

    # if there is no regex field, use first field (process name)
    if ( ($#line) < 1 )
    {
      $line[1] = $line[0];
    }

    # get process data
    push(@processes, GetProcInfo($line[0], $line[1], $ConfigurationData{'ExecutableFile_ps'}{'value'}, 
      $ConfigurationData{'ExecutableFile_lsof'}{'value'}));
  }
};
if ($@)
{
  chomp($@);
  print $OUT genXML($topVals, \@processes, $@);
  close $OUT;
  close $IN;
  copy($tmpout, $ConfigurationData{'out_file'}{'value'}) || die "Copy failed: $!";
  unlink($tmpout);
  exit 1;
}

close $IN;
print $OUT genXML($topVals, \@processes);
close $OUT;
copy($tmpout, $ConfigurationData{'out_file'}{'value'}) || die "Copy failed: $!";
unlink($tmpout);


