import React, {ChangeEvent, FormEvent, useState} from "react";
import {Button, Form, Row} from "react-bootstrap";
import Container from "react-bootstrap/Container";
import {CloudFrontScanner, textToIps} from "./CloudFrontScanner";


function Scanner() {

    const [isLoading, setLoading] = useState(false);

    const [ipRange, setIpRange] = useState("");
    const [scanner,] = useState(new CloudFrontScanner(window.location.hostname));

    return <Container>
        <Row>
            <Form>
              <Form.Group className="mb-3" controlId="formBasicEmail"  >
                <Form.Label>IPs to Scan</Form.Label>
                <Form.Control type="text" placeholder="IP CIDR" onChange={(e: ChangeEvent<HTMLInputElement>) => {
                    setIpRange(e.currentTarget.value);
                    console.log("ipRange: " + ipRange);
                }} />
                <Form.Text>
                  Enter the IP range to scan in CIDR notation.
                </Form.Text>
              </Form.Group>

              <Button
                  variant="primary"
                  // className="scan-shit"
                  disabled={isLoading}
                  onClick={isLoading ? undefined : () => {
                      scanner.scan(textToIps(ipRange));
                      setLoading(true);
                  }}
              >
                Submit
              </Button>
            </Form>
        </Row>
    </Container>
}

export default Scanner;
