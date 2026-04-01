data "aws_secretsmanager_secret" "db_credentials" {
  name = "paraearth_db_credentials"
}

data "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = data.aws_secretsmanager_secret.db_credentials.id
}

resource "aws_db_instance" "paraearth_postgres" {
  allocated_storage    = 100
  storage_type         = "gp3"
  engine               = "postgres"
  engine_version       = "16"
  instance_class       = "db.r6g.large"
  identifier           = "paraearth-db"
  username             = "postgres"
  password             = jsondecode(data.aws_secretsmanager_secret_version.db_credentials.secret_string)["password"]
  parameter_group_name = "default.postgres16"
  skip_final_snapshot  = false

  # Ensure pgvector extension is enabled upon init
}
