rsync\
 --progress\
 --recursive\
 --chmod=777\
 /home/ilan/Projects/osgscal/\
 root@test-001.t2.ucsd.edu:/home/ilan/osgscal 

ssh root@test-001.t2.ucsd.edu "chown -hR ilan /home/ilan"