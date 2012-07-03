// We don't want to load the mobile logo unless it's used
jQuery( document ).ready( function() {
	var mobileLogo = jQuery( "#mobile-logo" );
	if ( mobileLogo.length ) {
		mobileLogo.attr( "src", mobileLogo.data( "src" ) );
	}
} );
