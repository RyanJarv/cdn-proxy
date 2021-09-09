import React, {useEffect, useState} from "react";
import {Button, Col, Row} from "react-bootstrap";
import Container from "react-bootstrap/Container";

class CloudFrontScanner {
  constructor(origins) {
    this.origins = origins;
  }

  scan() {

  }
}

function simulateNetworkRequest() {
  return new Promise((resolve) => setTimeout(resolve, 2000));
}

function Scanner() {

    const [isLoading, setLoading] = useState(false);

    return <Container>
        <Row>
            <Col xs={{offset: 2}}>
                <Button className="justify-content-md-center scan-shit" >Scan Shit v1</Button>
            </Col>
        </Row>
        <Row>
            <Col xs={{offset: 2}}>
                <Button className="justify-content-md-center scan-shit" >Scan Shit v2</Button>
            </Col>
        </Row>
        <Row>
            <Col xs={{offset: 2}}>
                <Button
                    variant="danger"
                    className="scan-shit"
                    disabled={isLoading}
                    onClick={isLoading ? null : () => {
                        simulateNetworkRequest().then(() => {
                            setLoading(false);
                        });
                        setLoading(true)
                    }}
                >
                    Scan Shit v3
                </Button>
            </Col>
        </Row>
    </Container>
}

export default Scanner;
