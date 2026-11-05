# Retained results and contract correction

Suggested commit: `fix: prevent Pro runtime from falling back to Neon configuration`.

Initial RED20261105T140506017079Z:0pass/1fail/6unverified. Actual status configured=true with only a synthetic Neon variable while ProON;0driver/fetch attempts, child stopped.

First product run20261105T140535754321Z:2pass/1fail/4unverified. N01/N02 prove corrected origin selection and503pending; N03 correctly refused native access beforeSQL/driver but used the existing router's503 DATA_UNAVAILABLE contract. The pre-code expectation500 was mistaken: aws-app.handleRequest explicitly defaults unexpected configuration exceptions to503. Both N03/N05 expectations corrected to exact503/DATA_UNAVAILABLE/no-store/noSQL/no driver, preserving existing API error behavior. No product change was made to turn this mismatch green.
