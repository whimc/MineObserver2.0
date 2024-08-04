package edu.whimc.photographer;

import edu.whimc.observations.models.ObserveEvent;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;

public class Listeners implements Listener {

    private final Photographer plugin;

    public Listeners(Photographer plugin) {
        this.plugin = plugin;
    }

    @EventHandler
    public void onObservation(ObserveEvent event) {
        this.plugin.queueObservationPhotograph(event.getObservation());

        // Wait a few ticks for the hologram to spawn
        Bukkit.getScheduler().runTaskLater(this.plugin, () -> {
           CameraOperator.getAllCameraOperators().forEach(co ->
                   event.getObservation().getHologram().getVisibilityManager().hideTo(co.getPlayer()));
        }, 10);
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        Player player = event.getPlayer();
        CameraOperator.getCameraOperator(player.getUniqueId()).ifPresent(CameraOperator::unregister);
        CameraOperator.getAllCameraOperators().forEach(co -> co.getPlayer().showPlayer(this.plugin, player));
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        CameraOperator.getAllCameraOperators().forEach(co -> co.getPlayer().hidePlayer(this.plugin, event.getPlayer()));
    }
}
