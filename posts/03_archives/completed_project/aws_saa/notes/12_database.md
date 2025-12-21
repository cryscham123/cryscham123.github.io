# database choice in aws

## database types
- RDBMS(RDS, aurora): SQL, OLTP
- NoSQL: DynamoDB(JSON), ElasticCache(key / value), Neptune(graphs), DocumentDB(MongoDB), Keyspaces(Cassandra)
- Object storage: S3(for big), Glacier(for backup, archive)
- Data warehouse: SQL analytics, Redshift(OLAP), athena, EMR
- Search: openSearch(JSON)
- Graphs: Amazon Neptune
- Ledger: QLDB
- Time series: Timestream

### DocumentDB
- MongoDB compatible
- Fully managed
- highly available with replication across 3 AZs
- Automatically scales up to 10GB storage, millions of requests per seconds workloads

### Amazon Neptune
- Graph database
- Fully managed
- Highl available with replication across 3 AZs, up to 15 read replicas
- Supports up to billions of relations

### Amazon Keyspaces
- Cassandra compatible
- Fully managed
- Automatically scale tables based on traffic
- tables replicated across 3 times across multiple AZs
- ondemand, provisioned

### QLDB
- Ledger database
- Fully managed
- immutable, transparent, cryptographically verifiable transaction log
- high performance, low latency
- serverless, pay as you go
- no decentralized consensus, no blockchain

### Timestream
- Time series database
- Fully managed
- store and analyze trillions of events per day


