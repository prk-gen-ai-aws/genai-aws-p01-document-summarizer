# Version History

## v2 (Current)
- S3 bucket naming uses `random_id` suffix for global uniqueness
- Safe to destroy and recreate without naming conflicts
- **Use v2 for all deployments**

## v1 (Reference only)
- S3 bucket naming uses AWS account ID as suffix
- Kept for reference — shows the evolution of the IaC approach
- Not recommended for new deployments
- Superseded by v2
