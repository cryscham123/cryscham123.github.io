## Define IAM

### what is IAM
: identity access management (Global service)

### Groups
group by users (not group itself)

### Users
root account created by default
each users can have multi groups

## IAM:Policies
- Users or Groups can be assigned JSON documents called policies
- policies define permissions of the users(inline) or groups
- AWS apply the least privilege principle

### JSON exe
```JSON
{
	{
		"Version": "2012-10-17",
		// optional: "id": "...",
		"Statement": [
			{
				// optional: "Sid": "...",
				"Effect": "Allow",
				"Action": "s3:ListBucket",
				"Resource": "arn:aws:s3:::example-bucket"
			},
			{
				"Effect": "Allow",
				"Action": [
					"s3:GetObject",
					"s3:PutObject"
				],
				"Resource": "arn:aws:s3:::example-bucket/*"
			}
		]
	}
}
```

- Effect: Allow/Deny
- Principle: who can perform the action (account, user, role)
- Action: list of actions that are allowed or denied
- Resource: list of resources that are allowed or denied
- Condition: when the policy is in effect (optional)

## IAM:Roles for Services
- Roles are used to delegate permissions to entities that you trust

### trusted entities
- AWS account
- AWS services  
: EC2, Lambda, CodeBuild, CodePipeline, etc.

## IAM:Security Tools
- IAM Credentials Report (account level):  
	list of all users and their various credentials

- IAM Access Advisor (user level):  
	how long each service has been active and when it was last used
