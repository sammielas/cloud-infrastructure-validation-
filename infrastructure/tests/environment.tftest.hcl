run "accept_dev_environment" {
  command = plan

  variables {
    environment = "dev"
  }

  assert {
    condition     = output.environment == "dev"
    error_message = "Expected the environment output to equal dev."
  }
}

run "accept_test_environment" {
  command = plan

  variables {
    environment = "test"
  }

  assert {
    condition     = output.environment == "test"
    error_message = "Expected the environment output to equal test."
  }
}

run "accept_staging_environment" {
  command = plan

  variables {
    environment = "staging"
  }

  assert {
    condition     = output.environment == "staging"
    error_message = "Expected the environment output to equal staging."
  }
}

run "reject_production_environment" {
  command = plan

  variables {
    environment = "production"
  }

  expect_failures = [
    var.environment
  ]
}

run "default_environment_is_dev" {
  command = plan

  assert {
    condition     = output.environment == "dev"
    error_message = "Default environment must be dev."
  }
}
