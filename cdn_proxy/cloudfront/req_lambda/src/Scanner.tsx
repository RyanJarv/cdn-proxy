import React, {ChangeEvent, useState} from "react";
import {Button, Col, Form, Row} from "react-bootstrap";
import Container from "react-bootstrap/Container";
import {CloudFrontScanner, textToIps} from "./CloudFrontScanner";
import BootstrapTable from 'react-bootstrap-table-next';

const columns = [{
  dataField: 'origin',
  text: 'Origin'
}, {
  dataField: 'result',
  text: 'Result'
}];


function Scanner() {
    const [ipRange, setIpRange] = useState("");
    const [scanner,] = useState(new CloudFrontScanner(window.location.protocol + '//' + window.location.hostname));
    let [products, setProducts] = useState<Array<{ id: Number, origin: string; result: string; }>>([]);


    return <Container>
            <Form>
                <Row>
                    <Col sm={1}>
                        <Button
                            variant="primary"
                            type="submit"
                            onClick={() => {
                                for (const ip of textToIps(ipRange)) {
                                    scanner.cdnRequest(ip).then((resp) => {
                                            console.log("got successful response from " + ip);
                                            console.log(resp);
                                            setProducts((prev) => {
                                                let prevCopy = prev.slice()
                                                prevCopy.push({
                                                    'id': products.length,
                                                    'origin': ip,
                                                    'result': resp.status.toString(),
                                                }); return prevCopy
                                            })
                                        },
                                        (resp) => {
                                            console.log("got error response from " + ip);
                                            console.log(resp);
                                            setProducts((prev) => {
                                                let prevCopy = prev.slice()
                                                prevCopy.push({
                                                    'id': products.length,
                                                    'origin': ip,
                                                    'result': "request failed",
                                                }); return prevCopy
                                            })
                                        }
                                    );
                                }
                            }}
                        >
                            Submit
                        </Button>
                    </Col>

                    <Col sm={4}>
                        <Form.Group>
                          {/*<Form.Label>IPs to Scan</Form.Label>*/}
                          <Form.Control type="text" placeholder="IP CIDR" onChange={(e: ChangeEvent<HTMLInputElement>) => {
                              setIpRange(e.currentTarget.value);
                          }} />
                          <Form.Text>
                            Enter the IP range to scan in CIDR notation.
                          </Form.Text>
                        </Form.Group>
                    </Col>

                </Row>
            </Form>
        <Row>
            <Col sm={12}>
                <BootstrapTable keyField='id' data={ products } columns={ columns } />
            </Col>
        </Row>
    </Container>
}

export default Scanner;
