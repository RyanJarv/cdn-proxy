import React from 'react';
import {HashRouter, Route, Switch} from 'react-router-dom';
import {LinkContainer} from 'react-router-bootstrap';

import {Nav, Navbar, Row} from "react-bootstrap";
import Container from "react-bootstrap/Container";

import './App.css';
import Help from "./Help";
import Scanner from "./Scanner";

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
                </Nav>
            </Navbar.Collapse>
        </Container>
    </Navbar>
);

const OurNavBarRouter = () => (
    <HashRouter>
        <Switch>
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
                <Row>
                    <Help/>
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