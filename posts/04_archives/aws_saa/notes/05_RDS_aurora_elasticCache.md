# Amazon RDS
- Amazon RDS is a managed relational database service that provides a highly available, scalable, and secure database.
- Amazon RDS supports multiple database engines:
	- Amazon Aurora
	- MySQL
	- MariaDB
	- PostgreSQL
	- Oracle
	- Microsoft SQL Server
- Amazon RDS provides the following features:
	- Automated backups
	- Multi-AZ deployments
	- Read replicas
	- Monitoring
	- Security
	- Scalability
	- High availability
### auto scaling
- must set `maximum storage threshold`
1. free storage is less then 10% of allocated storage
2. low-storage lasts at least 5 minutes
3. 6 hours have passed since last modification

## RDS read replicas for read scalibity
- up to 15 read replicas
- within AZ, cross AZ, cross region (`dont pay for data transfer across AZ, not across region`)
- read replicas can be promoted to a standalone database

### cross AZ
- used for disaster recovery(not used for scaling)
- synchronous replication
- failover to standby in case of primary failure
- no manual intervention
### from single AZ to multi AZ
- zero downtime
- just modify for the database instance

## Amazon Aurora
- MySQL and PostgreSQL compatible
- cloud optimized (5 times faster than MySQL, 3 times faster than PostgreSQL)
- storage auto scaling
- 15 read replicas (cross region)
- failover instantaneously (less than 30 seconds through master node)
- cost more but effective
### High Availability and Read Scalability
- 6 copies of data across 3 AZs (4 copies is needed for write, 3 copies is needed for read)
- self-healing storage
- storage is striped across 100s of volumes

### Global aurora
- 1 primary region
- 5 read-only secondary regions
- replication lag is less than 1 second
- up to 16 read replicas per secondary region
- failover to secondary region
- `cross-region replication takes less than 1 second`

## backup
### RDS
- Automated backup (can disable, 5 minutes backup window)
- Manual snapshot (retention as log as you want)
- snapshot restore => new database
- s3 restore

### Aurora
- Automated backup (cannot disable, point-in-time recovery)
- Manual snapshot (retention as log as you want)
- snapshot restore => new database
- Percona XtraBackup, s3 restore

## security

## ElasticCache
- in-memory caching service
- Redis or Memcached (no high availability and backup)
- heavy application code change