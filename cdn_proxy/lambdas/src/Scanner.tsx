import React, {ChangeEvent, FormEvent, useState} from "react";
import {Button, Col, Form, Row, Table} from "react-bootstrap";
import Container from "react-bootstrap/Container";
import {CloudFrontScanner, textToIps} from "./CloudFrontScanner";
import BootstrapTable from 'react-bootstrap-table-next';

const columns = [{
  dataField: 'id',
  text: 'Product ID'
}, {
  dataField: 'url',
  text: 'URL'
}, {
  dataField: 'result',
  text: 'Result'
}];


function Scanner() {
    // const [isLoading, setLoading] = useState(false);

    const [ipRange, setIpRange] = useState("");
    const [scanner,] = useState(new CloudFrontScanner(window.location.hostname));
    let [products, setProducts] = useState<Array<{ id: Number, url: string; result: string; }>>([]);


    return <Container>
            <Form>
                <Row>
                    <Col sm={1}>
                        <Button
                            variant="primary"
                            type="submit"
                            // className="scan-shit"
                            // disabled={isLoading}
                            onClick={() => {
                                scanner.scan(
                                    textToIps(ipRange),
                                    (resp) => {
                                        console.log("response is: " + JSON.stringify(resp));
                                        console.log("products currently is: " + JSON.stringify(products));
                                        setProducts((prev) => {
                                            prev.push({
                                                'id': products.length,
                                                'url': resp.url,
                                                'result': resp.status.toString(),
                                            }); return prev
                                        })
                                    },
                                    (resp) => {
                                        console.log(resp);
                                    }
                                );
                                // setLoading(true);
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
                              console.log("ipRange: " + ipRange);
                              console.log("products: " + JSON.stringify(products));
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
