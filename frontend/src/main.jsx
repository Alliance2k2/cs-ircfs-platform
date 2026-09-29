import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Link, useNavigate } from "react-router-dom";
import "./styles/app.css";
import { authApi } from "./api/client.js";

const Home = () => <><h1>Climate-smart agriculture for Bugesera</h1><p>CS-IRCFS connects farmers, monitors, cooperatives, and district planners.</p><Link to="/login">Sign in</Link></>;
const About = () => <><h1>About CS-IRCFS</h1><p>A shared evidence platform for agriculture and irrigation decisions.</p></>;
const Login = () => { const [error,setError]=React.useState(""); const navigate=useNavigate(); async function submit(e){e.preventDefault(); const form=new FormData(e.currentTarget); try{const result=await authApi.login({email:form.get("email"),password:form.get("password")}); sessionStorage.setItem("cs_ircfs_session",result.access_token); navigate("/platform");}catch(err){setError(err.message);}} return <><h1>Sign in</h1><form onSubmit={submit}><label>Email<input name="email" type="email" required /></label><label>Password<input name="password" type="password" required /></label><button>Sign in</button>{error&&<p>{error}</p>}</form><Link to="/register">Create account</Link></>; };
const Register = () => { const [message,setMessage]=React.useState(""); async function submit(e){e.preventDefault(); const f=new FormData(e.currentTarget); try{await authApi.register({first_name:f.get("first_name"),surname:f.get("surname"),email:f.get("email"),password:f.get("password")});setMessage("Account request submitted.");}catch(err){setMessage(err.message);}} return <><h1>Create account</h1><form onSubmit={submit}><label>First name<input name="first_name" required /></label><label>Surname<input name="surname" required /></label><label>Email<input name="email" type="email" required /></label><label>Password<input name="password" type="password" required /></label><button>Create account</button></form><p>{message}</p></>; };
const Layout = () => <><header><Link to="/">CS-IRCFS</Link><nav><Link to="/about">About</Link><Link to="/login">Sign in</Link></nav></header><main><Routes><Route path="/" element={<Home/>}/><Route path="/about" element={<About/>}/><Route path="/login" element={<Login/>}/><Route path="/register" element={<Register/>}/><Route path="/platform" element={<h1>Platform</h1>}/></Routes></main></>;
createRoot(document.getElementById("root")).render(<BrowserRouter><Layout/></BrowserRouter>);


