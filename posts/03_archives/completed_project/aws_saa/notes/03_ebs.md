## what is ebs
- EBS is a network device designed to work with AWS EC2 instances.
- EBS volumes are placed in a specific AZ and are automatically replicated to protect you from component failure.
- EBS volumes attached only to one instance at a time.
- EBS volumes can be detached from one instance and attached to another.
- EBS volumes can be used as a boot volume.
- EBS volumes have a provisioned size and IOPS can be resized.
- EBS volumes can exist independently of an EC2 instance.
- multiple EBS volumes can be attached to a single EC2 instance.

### delete on termination
- By default, the root EBS volume is deleted when the EC2 instance is terminated.
- Additional EBS volumes are not deleted when the EC2 instance is terminated.

### EBS snapshots features
- EBS snapshots archive tier:  
75% cheaper than the general-purpose tier.  
takes 24 to 72 hours to restore.
- recycle bin:  
set up rule to retain deleted snapshots  
can specify period
- Fast Snapshot Restore(FSR):  
force full initialization of the EBS volume to have no latency  
takes money

### AMI
Amazon Machine Image
- AMI is a template that contains a software configuration (OS, application server, and applications) required to launch an EC2 instance.
- AMI is built for a `specific region`.
- can be copied to other regions.

### EC2 instance store
- `better IO performance` than EBS volumes
- `data is lost` when the instance is stopped or terminated.
- can't be resized.

### EBS volume types
- General Purpose SSD (gp2, gp3): `can be used for boot volumes`  
	- generally used for system boot volumes, virtual desktops, low-latency interactive apps, development, and test environments
	- gp2: 1GiB - 16TiB, burst up to 3000 IOPS `linked to volume size`
	- gp3: 1GiB - 16TiB, 3000 IOPS, 125MiB/s, burst up to 16000 IOPS, 1000MiB/s `independently`
- High Performance SSD (io1, io2): `can be used for boot volumes`
	- critical business applications that require sustained IOPS performance
	- `more than 16000 IOPS`
	- generally used for databases
	- 4GiB - 16TiB
	- Max PIOPS: `64000 for Nitro EC2`, 32000 for other EC2
	- Can increase PIOPS independently from volume size
	- io2 have more durability and more IOPS per GiB
	- io2 Block Express: 4GiB - 64TiB, `256000 IOPS`
	- `support Multi-Attach`  
		- bound in AZ
		- up to 16 EC2 instances
		- Must use a file system that is cluster-aware (GFS, OCFS2, NTFS)
- Low cost, designed for `frequently accessed` HDD (st1)  
	- 125MiB - 16TiB
	- 500MiB/s - 500MiB/s
	- used for big data, data warehouses, log processing
- Low cost, designed for `less frequently accessed` HDD (sc1)  
	- 125MiB - 16TiB
	- 250MiB/s - 250MiB/s
	- used for file servers, infrequently accessed workloads

### EFS
- Elastic File System
- `scalable` storage solution for EC2 instances
- `can be shared` across multiple instances `in multi-AZ`
- `can be accessed` by multiple instances simultaneously
- expensive than EBS
- can be used for ``content management`, `web serving`
- use NFSv4.1 protocol
- use `security group` to control access
- compatible with `Linux-based AMI`
- Performance Mode:
	- General Purpose: latency-sensitive use cases
	- Max I/O: higher latency, higher throughput
- Throughput Mode:
	- Bursting: burstable throughput
	- Provisioned: provisioned throughput
	- Elastic: elastic throughput
- storage classes:
	- Standard: frequently accessed
	- Infrequent Access: infrequently accessed
	- One Zone: infrequently accessed, stored in a single AZ. 90% cheaper than Regional
