# Pro requires RDS configuration

Suggested commit: `fix: prevent Pro runtime from falling back to Neon configuration`.

With ProON and no AWS database setting, the old configuration selector still declared itself configured using NEON_DATABASE_URL. Pro now selects the AWS configuration path and refuses a missing/non-RDS endpoint before the driver. Health returns503pending withoutSQL when unconfigured.

ActualNode24 E2E7/7:7HTTP requests across3owned HTTP children,0SQL,0driver connect attempts,0external fetches; all children stopped. The separate positive typed PG workflow remains14/14. Initial RED and the mistaken500-versus-existing503 expectation are retained with their exact inputs. This proves failure behavior under missing/wrong configuration, not measured production latency or complete Neon retirement. Production still uses its old bridge until full AWS backend qualification.
