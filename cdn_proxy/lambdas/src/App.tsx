import React from 'react';
import {HashRouter, Route, Switch} from 'react-router-dom';
import {LinkContainer} from 'react-router-bootstrap';

import {Nav, Navbar, NavDropdown, Row} from "react-bootstrap";
import Container from "react-bootstrap/Container";

import './App.css';
import Help from "./Help";
import Scanner from "./Scanner";

// // Example POST method implementation:
// async function proxyReq(url = '', data = {}) {
//     // Default options are marked with *
//     const response = await fetch(url, {
//         method: 'GET',
//         headers: {
//             'Cdn-Proxy-Origin': 'www.wikipedia.org',
//             'Cdn-Proxy-Host': 'www.wikipedia.org'
//         },
//         redirect: 'error', // manual, *follow, error
//     });
//     return response.json(); // parses JSON response into native JavaScript objects
// }
//
const OurNavBar = (props: any) => (
    <Navbar bg="light" expand="lg">
        <Container>
            <Navbar.Brand href="#home">{props.name}</Navbar.Brand>
            <Navbar.Toggle aria-controls="basic-navbar-nav" />
            <Navbar.Collapse id="basic-navbar-nav">
                <Nav className="me-auto">
                    <LinkContainer to="/">
                        <Nav.Link>Home</Nav.Link>
                    </LinkContainer>
                    <LinkContainer to="/scanner">
                        <Nav.Link>Scanner</Nav.Link>
                    </LinkContainer>
                    <LinkContainer to="/help">
                        <Nav.Link>Help</Nav.Link>
                    </LinkContainer>
                    <NavDropdown title="Dropdown" id="basic-nav-dropdown">
                        <NavDropdown.Item href="#action/3.1">Action</NavDropdown.Item>
                        <NavDropdown.Item href="#action/3.2">Another action</NavDropdown.Item>
                        <NavDropdown.Item href="#action/3.3">Something</NavDropdown.Item>
                        <NavDropdown.Divider />
                        <NavDropdown.Item href="#action/3.4">Separated link</NavDropdown.Item>
                    </NavDropdown>
                </Nav>
            </Navbar.Collapse>
        </Container>
    </Navbar>
);

const OurNavBarRouter = () => (
    <HashRouter>
        <Switch>
            <Route path="/help">
                <Row>
                    <OurNavBar name="Help" />
                </Row>
                <Row>
                    <Help/>
                </Row>
            </Route>
            <Route path="/scanner">
                <Row>
                    <OurNavBar name="Scanner" />
                </Row>
                <Row>
                    <Scanner/>
                </Row>
            </Route>
            <Route path="/">
                <Row>
                    <OurNavBar name="Home" />
                </Row>
            </Route>
        </Switch>
    </HashRouter>
);

const App = () => (
    <Container>
        <OurNavBarRouter/>
        <footer className="pt-5 my-5 text-muted border-top">
            Created by the RhinoSecurityLabs team &middot; &copy; 2021
        </footer>
    </Container>
);

export default App;