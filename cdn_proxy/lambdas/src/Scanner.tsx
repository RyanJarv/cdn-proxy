import React, {FormEvent, FormEventHandler, MouseEventHandler, useState} from "react";
import {Button, Col, Form, Row} from "react-bootstrap";
import Container from "react-bootstrap/Container";
import {CloudFrontScanner, textToIps} from "./CloudFrontScanner";


function simulateNetworkRequest() {
  return new Promise((resolve) => setTimeout(resolve, 2000));
}

function Scanner() {

    const [isLoading, setLoading] = useState(false);

    const [ipRange, setIpRange] = useState("");
    const [scanner, _] = useState(new CloudFrontScanner(window.location.hostname));

    return <Container>
        <Row>
            <Form>
              <Form.Group className="mb-3" controlId="formBasicEmail">
                <Form.Label>Email address</Form.Label>
                <Form.Control type="email" placeholder="IP Range" />
                <Form.Text className="text-muted" onChange={(e: FormEvent<HTMLElement>) => setIpRange(e.currentTarget.innerText)}>
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
