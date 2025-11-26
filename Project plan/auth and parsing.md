# DDNet Server Control

A C++ application for controlling DDNet servers through the ECON (External Console) protocol. This tool allows server administrators to remotely manage their DDNet servers with simple commands.

## Features

- TCP-based connection to DDNet servers
- ECON protocol authentication
- Server command execution
- Map name retrieval
- Real-time server response handling

## Prerequisites

- Windows operating system
- C++ compiler (Visual Studio recommended)
- DDNet server running with ECON enabled

## Building the Project

1. Clone this repository
2. Open the project in your preferred C++ IDE
3. Build the solution
4. Run the executable

## Server Configuration

Your DDNet server must have ECON enabled with the following settings in the server config:

```ini
ec_port = 8303
ec_password = "your_password"
sv_rcon_password = "your_rcon_password"
```

## Usage

1. Start your DDNet server
2. Run the DDNet Control application
3. The application will automatically:
   - Connect to the server
   - Authenticate using the ECON password
   - Retrieve current server information

## Example Commands

Currently implemented commands:
- `sv_map`: Retrieves the current map name

## Implementation Details

The application uses:
- Winsock API for network communication
- TCP sockets for reliable connection
- Standard C++ libraries for string manipulation

## Security Considerations

- Store passwords securely in a configuration file
- Use strong passwords for both ECON and RCON
- Limit access to the control application to trusted administrators

## Contributing

Feel free to contribute to this project by:
1. Forking the repository
2. Creating a feature branch
3. Submitting a pull request

## Future Enhancements

- Additional server commands support
- Player management features
- Configuration file support
- Enhanced error handling
- Logging system

## License

This project is open source and available under the MIT License.

## Acknowledgments

- DDNet Team for the server software
- Contributors to the ECON protocol documentation
